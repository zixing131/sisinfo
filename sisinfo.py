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

from sis import sisinfo, sisfields
import optparse
import sys, os

class Handler :
    def __init__(self) :
		self.files = []
		self.fileDatas = []
        
    def handleField(self, field, depth) :
		if field.type == sisfields.FileDescriptionField :
			self.files.append(field)
		elif field.type == sisfields.FileDataField :
			self.fileDatas.append(field)

    def execute(self, options) :
		for f in self.files :
			if options.info :
				buf = "   " + f.findField(sisfields.StringField)[0].readableStr()
				caps = f.findField(sisfields.CapabilitiesField)[0]
				if caps :
					buf += " [" + " ".join(f.findField(sisfields.CapabilitiesField)[0].readableCaps) + "]"
				print buf
			if options.extract :
				parts = f.findField(sisfields.StringField)[0].readableStr().split("\\")
				if len(parts[len(parts) - 1]) > 0 :
					path = os.path.abspath(options.extract)
					if not os.path.exists(path) :
						os.makedirs(path)
					newFile = file(path + "\\" + parts[len(parts) - 1], "wb")
					newFile.write(self.fileDatas[f.fileIndex].findField(sisfields.CompressedField)[0].data)
					newFile.close()
			
class ContentPrinter :
	def __init__(self) :
		pass
		
	def handleField(self, field, depth) :
		buf = ""
		for i in range(depth) :
			buf += "  "
		buf += sisfields.FieldNames[field.type] + " "
		if len(field.readableStr()) > 0 :
			buf += field.readableStr()
		print buf

OptionList = [
	optparse.make_option("-f", "--file", help="Name of the SIS file to inspect", metavar="FILENAME"),
	optparse.make_option("-i", "--info", help="Print information about SIS contents", action="store_true", default=False),
	optparse.make_option("-s", "--structure", help="Print SIS file structure", action="store_true", default=False),
	optparse.make_option("-e", "--extract", help="Extract the files from the SIS file to PATH", metavar="PATH")
	]
	
def validateArguments(options, args) :
	result = True
	if not options.file :
		result = False
		raise Exception("Filename must be defined")
	if not (options.structure or options.extract or options.info) :
		result = False
		raise Exception("At least one of the switches: -s, -e, or -i must be defined")
	return result
			
if __name__ == "__main__" :
	parser = optparse.OptionParser(option_list=OptionList)
	(options, args) = parser.parse_args(sys.argv)
	validArguments = False
	try :
		validArguments = validateArguments(options, args)
	except Exception, err:
		print "ERROR : " + str(err) + "\n"
		parser.print_help()
	
	if validArguments :
		sisInfo = sisinfo.SISInfo()
		sisInfo.parse(options.file)
		if options.structure :
			handler = ContentPrinter()
			sisInfo.traverse(handler)
		handler = Handler()
		sisInfo.traverse(handler)
		handler.execute(options)
