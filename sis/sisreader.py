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


import struct
import sisfields

class SISReader :
	def __init__(self) :
		pass
		
	def readUnsignedBytes(self, numBytes) :
		buf = self.readPlainBytes(numBytes)
		if len(buf) < numBytes :
			return []
			
		format = ""
		for i in range(numBytes) :
			format += "B"
		return struct.unpack(format, buf)
	
	def readSignedBytes(self, numBytes) :
		buf = self.readPlainBytes(numBytes)
		if len(buf) < numBytes :
			return []
			
		format = ""
		for i in range(numBytes) :
			format += "b"
		return struct.unpack(format, buf)
		
	def readBytesAsUint(self, numBytes) :
		result = 0
		bytes = self.readUnsignedBytes(numBytes)
		if len(bytes) == numBytes :
			for i in range(numBytes) :
				result |= bytes[i] << (i*8)
		
		return result
		
	def readBytesAsInt(self, numBytes) :
		result = 0
		bytes = self.readSignedBytes(numBytes)
		if len(bytes) == numBytes :
			for i in range(numBytes) :
				result |= bytes[i] << (i*8)
		
		return result
		
	def skipPadding(self) :
		result = 0
		if self.bytesRead % 4 != 0 :
			paddingLength = 4 - self.bytesRead % 4
			self.readPlainBytes(paddingLength)
			result = paddingLength
			
		return result
	

class SISFileReader(SISReader) : 
	def __init__(self, inStream) :
		self.inStream = inStream
		self.eof = False
		self.bytesRead = 0

	def readPlainBytes(self, numBytes) :
		if self.eof :
			return ""
			
		if numBytes == 0 :
			return ""
			
		buf = ""
		buf = self.inStream.read(numBytes)
		if len(buf) < numBytes :
			self.eof = True
			return ""
			
		self.bytesRead += numBytes
		
		return buf

	def isEof(self) :
		return self.eof
		
class SISBufferReader(SISReader) :
	def __init__(self, buffer) :
		self.buffer = buffer
		self.bytesRead = 0
		
	def readPlainBytes(self, numBytes) :
		if self.isEof() :
			return ""
			
		if numBytes == 0 :
			return ""
			
		result = self.buffer[self.bytesRead:self.bytesRead+numBytes]
			
		self.bytesRead += numBytes
		
		return result
			
	def isEof(self) :
		return self.bytesRead >= len(self.buffer)
		
class SISFieldParser :
	def __init__(self) :
		self.lastReadBytes = 0
		
	def parseField(self, fileReader) :
		"""Reads the next field from the fileReader stream and returns it"""
		field = None
		self.lastReadBytes = 0
		type = fileReader.readBytesAsUint(4)
		self.lastReadBytes += 4
		if type != 0 :
			field = sisfields.SISFieldTypes[type]()
			field.type = type
			field.initFromFile(fileReader)
			self.lastReadBytes += field.length + 4 # Field length + length field
			self.lastReadBytes += fileReader.skipPadding()
		return field
