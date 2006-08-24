"""
Copyright (c) 2006, Jari Sukanen
All rights reserved.

Redistribution and use in source and binary forms, with or 
without modification, are permitted provided that the following 
conditions are met:
	* Redistributions of source code must retain the above copyright 
	  notice, this list of conditions and the following disclaimer.
    * Redistributions in binary form must reproduce the above copyright 
	  notice, this list of conditions and the following disclaimer in 
	  the documentation and/or other materials provided with the 
	  distribution.
    * Names of the contributors may not be used to endorse or promote 
	  products derived from this software without specific prior written 
	  permission.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS 
"AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED 
TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR 
PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS 
BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR 
CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF 
SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS 
INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN 
CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) 
ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF 
THE POSSIBILITY OF SUCH DAMAGE.
"""

import sisreader 
import zlib

class SISFileHeader :
	def __init__(self) :
		self.uid1 = 0
		self.uid2 = 0
		self.uid3 = 0
		self.uidChecksum = 0

class SISField :
	def __init__(self) :
		self.type = 0
		self.length = None
		self.subFields = []
		
	def readFieldLength(self, fileReader) :
		length = fileReader.readBytesAsUint(4)
		if length & 0x80000000 > 0 :
			length = length << 32
			length |= fileReader.readBytesAsUint(4)
		return length
		
	def findField(self, fieldType, startIndex = 0) :
		result = None
		index = startIndex
		
		for field in self.subFields[startIndex:] :
			if field.type == fieldType :
				result = field
				break
			++index
		return (result, index)
		
	def readableStr(self) :
		return ""
	
	def traverse(self, handler, depth = 0) :
		handler.handleField(self, depth)
		for field in self.subFields :
			field.traverse(handler, depth + 1)
		
class SISUnsupportedField(SISField) :
	def __init__(self) :
		SISField.__init__(self)
		
	def initFromFile(self, fileReader) :
		self.length = self.readFieldLength(fileReader)
		fileReader.readPlainBytes(self.length)

class SISStringField(SISField) :
	def __init__(self) :
		SISField.__init__(self)
		self.data = None
		
	def initFromFile(self, fileReader) :
		self.length = self.readFieldLength(fileReader)
		buf = fileReader.readPlainBytes(self.length)
		self.data = buf.decode("utf-16")
		
	def readableStr(self) :
		return self.data
		
class SISArrayField(SISField) :
	def __init__(self) :
		SISField.__init__(self)
		
	def initFromFile(self, fileReader) :
		self.length = self.readFieldLength(fileReader)
		type = fileReader.readBytesAsInt(4)
		l = self.length - 4
		while l > 0 :
			field = SISFieldTypes[type]()
			field.type = type
			field.initFromFile(fileReader)
			self.subFields.append(field)
			
			l -= field.length + 4 # field length + the length field
			padding = fileReader.skipPadding()
			l -= padding

class SISCompressedField(SISField) :
	def __init__(self) :
		SISField.__init__(self)
		self.algorithm = None
		self.uncompressedDataSize = None
		self.data = None
		
	def initFromFile(self, fileReader) :
		self.length = self.readFieldLength(fileReader)
		self.algorithm = fileReader.readBytesAsUint(4)
		self.uncompressedDataSize = fileReader.readBytesAsUint(8)
		data = fileReader.readPlainBytes(self.length - 4 - 8)
		if self.algorithm == 0 :
			self.data = data
		elif self.algorithm == 1 :
			self.data = zlib.decompress(data)
			
class SISVersionField(SISField) :
	def __init__(self) :
		SISField.__init__(self)
		self.version = (-1, -1, -1)
		
	def initFromFile(self, fileReader) :
		self.length = self.readFieldLength(fileReader)
		major = fileReader.readBytesAsInt(4)
		minor = fileReader.readBytesAsInt(4)
		build = fileReader.readBytesAsInt(4)
		self.version = (major, minor, build)
		
	def readableStr(self) :
		return str(self.version)
	
class SISVersionRangeField(SISField) :
	def __init__(self) :
		SISField.__init__(self)
		self.fromVersion = None
		self.toVersion = None
		
	def initFromFile(self, fileReader) :
		self.length = self.readFieldLength(fileReader)
		fieldParser = sisreader.SISFieldParser()
		self.fromVersion = fieldParser.parseField(fileReader)
		self.toVersion = fieldParser.parseField(fileReader)
	
class SISDateField(SISField) :
	def __init__(self) :
		SISField.__init__(self)
		self.year = None
		self.month = None
		self.day = None
		
	def initFromFile(self, fileReader) :
		self.length = self.readFieldLength(fileReader)
		self.year = fileReader.readBytesAsUint(2)
		self.month = fileReader.readBytesAsUint(1)
		self.day = fileReader.readBytesAsUint(1)
	
	def readableStr(self) :
		return str(self.year) + "." + str(self.month) + "." + str(self.day)
	
class SISTimeField(SISField) :
	def __init__(self) :
		SISField.__init__(self)
		self.hours = None
		self.minutes = None
		self.seconds = None
		
	def initFromFile(self, fileReader) :
		self.length = self.readFieldLength(fileReader)
		self.hours = fileReader.readBytesAsUint(1)
		self.minutes = fileReader.readBytesAsUint(1)
		self.seconds = fileReader.readBytesAsUint(1)
	
	def readableStr(self) :
		return str(self.hours) + ":" + str(self.minutes) + ":" + str(self.seconds)
	
class SISDateTimeField(SISField) :
	def __init__(self) :
		SISField.__init__(self)
		self.date = None
		self.time = None
		
	def initFromFile(self, fileReader) :
		self.length = self.readFieldLength(fileReader)
		fieldParser = sisreader.SISFieldParser()
		self.date = fieldParser.parseField(fileReader)
		self.time = fieldParser.parseField(fileReader)
	
class SISUidField(SISField) :
	def __init__(self) :
		SISField.__init__(self)
		self.uid = None
		
	def initFromFile(self, fileReader) :
		self.length = self.readFieldLength(fileReader)
		self.uid = fileReader.readBytesAsUint(4)
		
	def readableStr(self) :
		return hex(self.uid)
	
class SISLanguageField(SISField) :
	def __init__(self) :
		SISField.__init__(self)
		self.language = None
		
	def initFromFile(self, fileReader) :
		self.length = self.readFieldLength(fileReader)
		self.language = fileReader.readBytesAsUint(4)
		
	def readableStr(self) :
		return str(self.language)
	
class SISContentsField(SISField) :
	def __init__(self) :
		SISField.__init__(self)
		
	def initFromFile(self, fileReader) :
		self.length = self.readFieldLength(fileReader)
		fieldParser = sisreader.SISFieldParser()
		field = fieldParser.parseField(fileReader)
		while field :
			if field.type == 3 : # compressed<conroller>
				bufferReader = sisreader.SISBufferReader(field.data)
				field = fieldParser.parseField(bufferReader)
			self.subFields.append(field)
			field = fieldParser.parseField(fileReader)

class SISControllerField(SISField) :
	def __init__(self) :
		SISField.__init__(self)
		
	def initFromFile(self, fileReader) :
		self.length = self.readFieldLength(fileReader)
		fieldParser = sisreader.SISFieldParser()
		bufferReader = sisreader.SISBufferReader(fileReader.readPlainBytes(self.length))
		field = fieldParser.parseField(bufferReader)
		while field :
			self.subFields.append(field)
			field = fieldParser.parseField(bufferReader)

class SISInfoField(SISField) :
	def __init__(self) :
		SISField.__init__(self)
		self.installType = None
		self.installFlags = None
		
	def initFromFile(self, fileReader) :
		self.length = self.readFieldLength(fileReader)
		fieldParser = sisreader.SISFieldParser()
		self.subFields.append(fieldParser.parseField(fileReader)) # UID
		self.subFields.append(fieldParser.parseField(fileReader)) # Vendor name unique
		self.subFields.append(fieldParser.parseField(fileReader)) # names
		self.subFields.append(fieldParser.parseField(fileReader)) # vendor names
		self.subFields.append(fieldParser.parseField(fileReader)) # version
		self.subFields.append(fieldParser.parseField(fileReader)) # creation time
		self.installType = fileReader.readBytesAsUint(1)
		self.installFlags = fileReader.readBytesAsUint(1) 
			
class SISSupportedLanguagesField(SISField) :
	def __init__(self) :
		SISField.__init__(self)
		
	def initFromFile(self, fileReader) :
		self.length = self.readFieldLength(fileReader)
		fieldParser = sisreader.SISFieldParser()
		self.subFields.append(fieldParser.parseField(fileReader)) # languages
		
class SISSupportedOptionsField(SISField) :
	def __init__(self) :
		SISField.__init__(self)
		
	def initFromFile(self, fileReader) :
		self.length = self.readFieldLength(fileReader)
		fieldParser = sisreader.SISFieldParser()
		self.subFields.append(fieldParser.parseField(fileReader)) # options
			
class SISPrerequisitiesField(SISField) :
	def __init__(self) :
		SISField.__init__(self)
		
	def initFromFile(self, fileReader) :
		self.length = self.readFieldLength(fileReader)
		fieldParser = sisreader.SISFieldParser()
		self.subFields.append(fieldParser.parseField(fileReader)) # target devices
		self.subFields.append(fieldParser.parseField(fileReader)) # dependencies
		
class SISDependencyField(SISField) :
	def __init__(self) :
		SISField.__init__(self)
		
	def initFromFile(self, fileReader) :
		self.length = self.readFieldLength(fileReader)
		fieldParser = sisreader.SISFieldParser()
		self.subFields.append(fieldParser.parseField(fileReader)) # UID
		self.subFields.append(fieldParser.parseField(fileReader)) # version range
		self.subFields.append(fieldParser.parseField(fileReader)) # dependency names
	
class SISPropertiesField(SISField) :
	def __init__(self) :
		SISField.__init__(self)
		
	def initFromFile(self, fileReader) :
		self.length = self.readFieldLength(fileReader)
		fieldParser = sisreader.SISFieldParser()
		self.subFields.append(fieldParser.parseField(fileReader)) # properties
	
class SISPropertyField(SISField) :
	def __init__(self) :
		SISField.__init__(self)
		self.key = None
		self.value = None
		
	def initFromFile(self, fileReader) :
		self.length = self.readFieldLength(fileReader)
		self.key = fileReader.readBytesAsInt(4)
		self.value = fileReader.readBytesAsInt(4)
	
# There is a type for this field, but there is no definition of the field contents
class SISSignaturesField(SISUnsupportedField) :
	pass
	
class SISCertificateChainField(SISField) :
	def __init__(self) :
		SISField.__init__(self)
		
	def initFromFile(self, fileReader) :
		self.length = self.readFieldLength(fileReader)
		fieldParser = sisreader.SISFieldParser()
		self.subFields.append(fieldParser.parseField(fileReader)) # certificate data
	
class SISLogoField(SISField) :
	def __init__(self) :
		SISField.__init__(self)

	def initFromFile(self, fileReader) :
		self.length = self.readFieldLength(fileReader)
		fieldParser = sisreader.SISFieldParser()
		self.subFields.append(fieldParser.parseField(fileReader)) # logo file
	
class SISFileDescriptionField(SISField) :
	def __init__(self) :
		SISField.__init__(self)
		self.operation = None
		self.operationOptions = None
		self.compressedLength = None
		self.uncompressedLength = None
		self.fileIndex = None
		
	def initFromFile(self, fileReader) :
		self.length = self.readFieldLength(fileReader)
		fieldParser = sisreader.SISFieldParser()
		
		self.subFields.append(fieldParser.parseField(fileReader))
		self.subFields.append(fieldParser.parseField(fileReader))
		field = fieldParser.parseField(fileReader)
		self.subFields.append(field)
		if field.type == 41 : # read field was capabilities ==> there is one more field left
			self.subFields.append(fieldParser.parseField(fileReader))
		
		self.operation = fileReader.readBytesAsUint(4)
		self.operationOptions = fileReader.readBytesAsUint(4)
		self.compressedLength = fileReader.readBytesAsUint(8)
		self.uncompressedLength = fileReader.readBytesAsUint(8)
		self.fileIndex = fileReader.readBytesAsUint(4)
		
	def readableStr(self) :
		return "index: " + str(self.fileIndex)
	
class SISHashField(SISField) :
	def __init__(self) :
		SISField.__init__(self)
		self.algorithm = None

	def initFromFile(self, fileReader) :
		self.length = self.readFieldLength(fileReader)
		fieldParser = sisreader.SISFieldParser()
		self.algorithm = fileReader.readBytesAsUint(4)
		self.subFields.append(fieldParser.parseField(fileReader)) # logo file
	
class SISIfField(SISField) :
	def __init__(self) :
		SISField.__init__(self)

	def initFromFile(self, fileReader) :
		self.length = self.readFieldLength(fileReader)
		fieldParser = sisreader.SISFieldParser()
		self.subFields.append(fieldParser.parseField(fileReader)) # expression
		self.subFields.append(fieldParser.parseField(fileReader)) # install block
		self.subFields.append(fieldParser.parseField(fileReader)) # else ifs

class SISElseIfField(SISField) :
	def __init__(self) :
		SISField.__init__(self)

	def initFromFile(self, fileReader) :
		self.length = self.readFieldLength(fileReader)
		fieldParser = sisreader.SISFieldParser()
		self.subFields.append(fieldParser.parseField(fileReader)) # expression
		self.subFields.append(fieldParser.parseField(fileReader)) # install block
	
class SISInstallBlockField(SISField) :
	def __init__(self) :
		SISField.__init__(self)
		self.files = None
		self.embeddedSISFiles = None
		self.ifBlocks = None
		
	def initFromFile(self, fileReader) :
		self.length = self.readFieldLength(fileReader)
		fieldParser = sisreader.SISFieldParser()
		self.subFields.append(fieldParser.parseField(fileReader))
		self.subFields.append(fieldParser.parseField(fileReader))
		self.subFields.append(fieldParser.parseField(fileReader))

class SISExpressionField(SISField) :
	def __init__(self) :
		SISField.__init__(self)
		self.operator = None
		self.integerValue = None
		
	def initFromFile(self, fileReader) :
		self.length = self.readFieldLength(fileReader)
		fieldParser = sisreader.SISFieldParser()
		self.operator = fileReader.readBytesAsUint(4)
		self.integerValue = fileReader.readBytesAsInt(4)
		
		if self.operator == 10 or self.operator == 13 :
			self.subFields.append(fieldParser.parseField(fileReader))
		if self.operator == 1 or self.operator == 2 or self.operator == 3 or self.operator == 4 or self.operator == 5 or self.operator == 6 or self.operator == 7 or self.operator == 8 or self.operator == 11 or self.operator == 12 :
			self.subFields.append(fieldParser.parseField(fileReader))
		if not (self.operator == 13 or self.operator == 14 or self.operator == 15 or self.operator == 16 or self.operator == 10) :
			self.subFields.append(fieldParser.parseField(fileReader))
		
class SISDataField(SISField) :
	def __init__(self) :
		SISField.__init__(self)
		
	def initFromFile(self, fileReader) :
		self.length = self.readFieldLength(fileReader)
		fieldParser = sisreader.SISFieldParser()
		self.subFields.append(fieldParser.parseField(fileReader)) # data units
	
class SISDataUnitField(SISField) :
	def __init__(self) :
		SISField.__init__(self)
		
	def initFromFile(self, fileReader) :
		self.length = self.readFieldLength(fileReader)
		fieldParser = sisreader.SISFieldParser()
		self.subFields.append(fieldParser.parseField(fileReader)) # file data
	
class SISFileDataField(SISField) :
	def __init__(self) :
		SISField.__init__(self)
		
	def initFromFile(self, fileReader) :
		self.length = self.readFieldLength(fileReader)
		fieldParser = sisreader.SISFieldParser()
		self.subFields.append(fieldParser.parseField(fileReader)) # raw file data
	
class SISSupportedOptionField(SISField) :
	def __init__(self) :
		SISField.__init__(self)
		
	def initFromFile(self, fileReader) :
		self.length = self.readFieldLength(fileReader)
		fieldParser = sisreader.SISFieldParser()
		self.subFields.append(fieldParser.parseField(fileReader)) # names
	
class SISControllerChecksumField(SISField) :
	def __init__(self) :
		SISField.__init__(self)
		self.checksum = None
		
	def initFromFile(self, fileReader) :
		self.length = self.readFieldLength(fileReader)
		self.checksum = fileReader.readBytesAsUint(2)
	
class SISDataChecksumField(SISField) :
	def __init__(self) :
		SISField.__init__(self)
		self.checksum = None
		
	def initFromFile(self, fileReader) :
		self.length = self.readFieldLength(fileReader)
		self.checksum = fileReader.readBytesAsUint(2)
	
class SISSignatureField(SISField) :
	def __init__(self) :
		SISField.__init__(self)
		
	def initFromFile(self, fileReader) :
		self.length = self.readFieldLength(fileReader)
		fieldParser = sisreader.SISFieldParser()
		self.subFields.append(fieldParser.parseField(fileReader)) # signature algorithm
		self.subFields.append(fieldParser.parseField(fileReader)) # signature data
	
class SISBlobField(SISField) :
	def __init__(self) :
		SISField.__init__(self)
		self.data = None
		
	def initFromFile(self, fileReader) :
		self.length = self.readFieldLength(fileReader)
		self.data = fileReader.readPlainBytes(self.length)
	
class SISSignatureAlgorithmField(SISField) :
	def __init__(self) :
		SISField.__init__(self)
		
	def initFromFile(self, fileReader) :
		self.length = self.readFieldLength(fileReader)
		fieldParser = sisreader.SISFieldParser()
		self.subFields.append(fieldParser.parseField(fileReader)) # algorithm identifier
	
class SISSignatureCertificateChainField(SISField) :
	def __init__(self) :
		SISField.__init__(self)
		
	def initFromFile(self, fileReader) :
		self.length = self.readFieldLength(fileReader)
		fieldParser = sisreader.SISFieldParser()
		self.subFields.append(fieldParser.parseField(fileReader)) # signatures
		self.subFields.append(fieldParser.parseField(fileReader)) # certificate chain
	
class SISDataIndexField(SISField) :
	def __init__(self) :
		SISField.__init__(self)
		self.dataIndex = None
		
	def initFromFile(self, fileReader) :
		self.length = self.readFieldLength(fileReader)
		self.dataIndex = fileReader.readBytesAsUint(4)

class SISCapabilitiesField(SISField) :
	def __init__(self) :
		SISField.__init__(self)
		self.capabilities = 0
		self.readableCaps = []
		
	def initFromFile(self, fileReader) :
		self.length = self.readFieldLength(fileReader)
		self.capabilities = fileReader.readBytesAsUint(self.length)
		
		for i in range(20) :
			if (self.capabilities >> i) & 0x01 :
				self.readableCaps.append(CapabilityNames[i])
				
	def readableStr(self) :
		return " ".join(self.readableCaps)
	
SISFieldTypes = { 
	1 : SISStringField,
	2 : SISArrayField,
	3 : SISCompressedField,
	4 : SISVersionField,
	5 : SISVersionRangeField,
	6 : SISDateField,
	7 : SISTimeField,
	8 : SISDateTimeField,
	9 : SISUidField,
	10 : SISUnsupportedField,
	11 : SISLanguageField,
	12 : SISContentsField,
	13 : SISControllerField,
	14 : SISInfoField,
	15 : SISSupportedLanguagesField,
	16 : SISSupportedOptionsField,
	17 : SISPrerequisitiesField,
	18 : SISDependencyField,
	19 : SISPropertiesField,
	20 : SISPropertyField,
	21 : SISSignaturesField,
	22 : SISCertificateChainField,
	23 : SISLogoField,
	24 : SISFileDescriptionField,
	25 : SISHashField,
	26 : SISIfField,
	27 : SISElseIfField,
	28 : SISInstallBlockField,
	29 : SISExpressionField,
	30 : SISDataField,
	31 : SISDataUnitField,
	32 : SISFileDataField,
	33 : SISSupportedOptionField,
	34 : SISControllerChecksumField,
	35 : SISDataChecksumField,
	36 : SISSignatureField,
	37 : SISBlobField,
	38 : SISSignatureAlgorithmField,
	39 : SISSignatureCertificateChainField,
	40 : SISDataIndexField,
	41 : SISCapabilitiesField
	}

[StringField, 
 ArrayField, 
 CompressedField,
 VersionField,
 VersionRangeField,
 DateField,
 TimeField,
 DateTimeField,
 UidField,
 UnusedField,
 LanguageField,
 ContentsField,
 ControllerField,
 InfoField,
 SupportedLanguagesField,
 SupportedOptionsField,
 PrerequisitiesField,
 DependencyField,
 PropertiesField,
 PropertyField,
 SignaturesField,
 CertificateChainField,
 LogoField,
 FileDescriptionField,
 HashField,
 IfField,
 ElseIfField,
 InstallBlockField,
 ExpressionField,
 DataField,
 DataUnitField,
 FileDataField,
 SupportedOptionField,
 ControllerChecksumField,
 DataChecksumField,
 SignatureField,
 BlobField,
 SignatureAlgorithmField,
 SignatureCertificateChainField,
 DataIndexField,
 CapabilitiesField] = range(1, 42)
	 
FieldNames = {
 0 : "ROOT",
 StringField : "StringField", 
 ArrayField : "ArrayField", 
 CompressedField : "CompressedField",
 VersionField : "VersionField",
 VersionRangeField : "VersionRangeField",
 DateField : "DateField",
 TimeField : "TimeField",
 DateTimeField : "DateTimeField",
 UidField : "UidField",
 UnusedField : "UnusedField",
 LanguageField : "LanguageField",
 ContentsField : "ContentsField",
 ControllerField : "ControllerField",
 InfoField : "InfoField",
 SupportedLanguagesField : "SupportedLanguagesField",
 SupportedOptionsField : "SupportedOptionsField",
 PrerequisitiesField : "PrerequisitiesField",
 DependencyField : "DependencyField",
 PropertiesField : "PropertiesField",
 PropertyField : "PropertyField",
 SignaturesField : "SignaturesField",
 CertificateChainField : "CertificateChainField",
 LogoField : "LogoField",
 FileDescriptionField : "FileDescriptionField",
 HashField : "HashField",
 IfField : "IfField",
 ElseIfField : "ElseIfField",
 InstallBlockField : "InstallBlockField",
 ExpressionField : "ExpressionField",
 DataField : "DataField",
 DataUnitField : "DataUnitField",
 FileDataField : "FileDataField",
 SupportedOptionField : "SupportedOptionField",
 ControllerChecksumField : "ControllerChecksumField",
 DataChecksumField : "DataChecksumField",
 SignatureField : "SignatureField",
 BlobField : "BlobField",
 SignatureAlgorithmField : "SignatureAlgorithmField",
 SignatureCertificateChainField : "SignatureCertificateChainField",
 DataIndexField : "DataIndexField",
 CapabilitiesField : "CapabilitiesField"
}
	 
CapabilityNames = {
	0 : "TCB",
	1 : "CommDD",
	2 : "PowerMgmt",
	3 : "MultimediaDD",
	4 : "ReadDeviceData",
	5 : "WriteDeviceData",
	6 : "DRM",
	7 : "TrustedUI",
	8 : "ProtServ",
	9 : "DiskAdmin",
	10 : "NetworkControl",
	11 : "AllFiles",
	12 : "SwEvent",
	13 : "NetworkServices",
	14 : "LocalServices",
	15 : "ReadUserData",
    16 : "WriteUserData",
	17 : "Location",
	18 : "SurroundingsDD",
	19 : "UserEnvironment"
	}