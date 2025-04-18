import json
import base64
from io import BytesIO
from pypdf import PdfReader, PdfWriter
from wsgiref.simple_server import make_server
import falcon

from typing import List

# https://stackoverflow.com/a/56930261
class DynamicAccessNestedDict:
    """Dynamically get/set nested dictionary keys of 'data' dict"""

    def __init__(self, data: dict):
        self.data = data

    def getval(self, keys: List):
        data = self.data
        for k in keys:
            data = data[k]
        return data

    def setval(self, keys: List, val) -> None:
        data = self.data
        lastkey = keys[-1]
        for k in keys[:-1]:  # when assigning drill down to *second* last key
            data = data[k]
        data[lastkey] = val

def generatePDF(nestedDict):
    with open("./test-data/fhtagn-charactersheet-v14.pdf", "rb") as fh:
        bytes_stream = BytesIO(fh.read())

    # Read from bytes_stream
    reader = PdfReader(bytes_stream)
    writer = PdfWriter()

    fields = reader.get_fields()

    writer.append(reader)

    writer.update_page_form_field_values(
        writer.pages[0],
        {"Name": nestedDict.getval(["characterData","personalInformation","firstName"])},
        auto_regenerate=False,
    )

    with BytesIO() as bytes_stream:
        bytes_stream_output = writer.write(bytes_stream)
        b = base64.b64encode(bytes_stream_output[1].getvalue())
        pdf_base64 = b.decode('utf8')
        return pdf_base64
        # pdf_base64 can be displayed in an iFrame by prepending "data:application/pdf;base64," and putting it in the src-Attribute

    #with open('./test-data/characterData.json', 'r') as file:
        #data = json.load(file)
        # print(data['modifications'])


# Falcon follows the REST architectural style, meaning (among
# other things) that you think in terms of resources and state
# transitions, which map to HTTP verbs.
class CharacterSheetResource:
    def on_post(self, req, resp):
        # Receive JSON with character data (see test data)
        data = req.stream.read(req.content_length or 0)
        jsonData = json.loads(data)
        nestedDict = DynamicAccessNestedDict(jsonData)

        # Generate the PDF and get the Base64 String bac
        base64_pdf_string = generatePDF(nestedDict)

        resp.status = falcon.HTTP_200  # This is the default status
        resp.content_type = falcon.MEDIA_TEXT  # Default is JSON, so override
        resp.text = (base64_pdf_string)


# falcon.App instances are callable WSGI apps
# in larger applications the app is created in a separate file
app = falcon.App(middleware=falcon.CORSMiddleware(allow_origins='*', allow_credentials='*'))

# Resources are represented by long-lived class instances
characterSheet = CharacterSheetResource()

# Routes
app.add_route('/pdf-character-sheet', characterSheet)

if __name__ == '__main__':
    with make_server('', 8000, app) as httpd:
        print('Serving on port 8000...')

        # Serve until process is killed
        httpd.serve_forever()

# Test with: curl -X POST -d '@test-data/characterData.json' localhost:8000/pdf-character-sheet
# will print nothing to the server right now
# will print the base64 string to the client, can be added to the <iframe> but inconvenient for testing