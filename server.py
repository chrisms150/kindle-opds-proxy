from flask import Flask, request, send_file
import requests
import feedparser
import urllib
import mobi
import subprocess
import os
import time

app = Flask(__name__)

opds_url = "YOURURLHERE"
opds_urlParsed = urllib.parse.urlsplit(opds_url)
opdsBaseURL = urllib.parse.urlunsplit((opds_urlParsed.scheme, opds_urlParsed.netloc, opds_urlParsed.path, '', ''))
opdsBaseURL = opdsBaseURL+'/'
baseUrlParts = [x for x in opds_urlParsed.path.split('/') if x]
# opdsBaseURL = urllib.parse.url
user = "USER"
password = "PASSWORD"

def html_maker(response):
    feed = feedparser.parse(response.content)
    htmlOut = ""
    htmlOut = htmlOut + f"<h1>Catalog: {feed.feed.title}</h1>"
    for entry in feed.entries:
        htmlOut = htmlOut + f"<h2>Title: {entry.title}</h2>"
        # Access links for EPUBs, images, or further navigation
        if 'links' in entry:
            for link in entry.links:
                htmlOut = htmlOut + f"<h3> - {link.rel}: {link.href}</h3>"
                match str(link.rel):
                    case 'subsection':
                        htmlOut = htmlOut + '<b>I am a subsection</b>'
                        htmlOut = htmlOut + f"<h3><a href={link.href}>link</a></h3>"
                    case "alternate":
                        htmlOut = htmlOut + "I am a alternate (CWA)"
                        htmlOut = htmlOut + f"<h3><a href={link.href}>link</a></h3>"
                    case "http://opds-spec.org/image":
                        htmlOut = htmlOut + f'I am an image. I\'ll deal with this later'
                    case "http://opds-spec.org/image/thumbnail":
                        htmlOut = htmlOut + f'I am a thumbnail. Deal with this later'
                    case 'http://opds-spec.org/acquisition':
                        # downloadPath = urllib.parse.urljoin(opdsBaseURL, link.href)
                        downloadPath = '/download' + str(link.href) + 'book.mobi'
                        htmlOut = htmlOut + f'I am a <a href={downloadPath}> download </a>'
                    case _:
                        htmlOut = htmlOut + f'<b>I am a {str(link.rel)} and I don\'t know how to handle this yet'
    return htmlOut

def convert_epub_to_mobi_calibre(epub_file_path, mobi_output_path):
    """
    Converts an EPUB file to MOBI format using Calibre's ebook-convert CLI tool.

    Args:
        epub_file_path (str): The path to the input EPUB file.
        mobi_output_path (str): The path for the output MOBI file.
    """
    command = ['ebook-convert', epub_file_path, mobi_output_path]

    try:
        # Run the command
        subprocess.run(command, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        # return send_file(os.path.abspath(mobi_output_path), as_attachment=True, download_name='test.mobi',
        #                 mimetype='application/x-mobipocket-ebook')
        return(os.path.abspath(mobi_output_path))
    except subprocess.CalledProcessError as e:
        return(f"Error during conversion: {e.stderr.decode()}")
    except FileNotFoundError:
        return("Error: ebook-convert not found. Make sure Calibre is installed and in your PATH.")


def download_handler(path):
    # Trigger the download
    downloadURL = opdsBaseURL + '/'.join(path.split('/')[1:-1])
    
    response = requests.get(downloadURL, stream=True, auth=(user, password))
    
    if response.status_code == 200:
        # Set a local filename (e.g., book.epub)
        with open("book.epub", "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        convertResponse = convert_epub_to_mobi_calibre('book.epub', 'book.mobi')
        return(convertResponse)
    else:
        return(f"Failed to download. Status: {response.status_code}")


@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def landing_page(path):
    search_query = request.args.get('query', default="")
    queries = request.args
    pathParts = [x for x in path.split('/') if x]
    combinedPath = '/'.join([part for part in pathParts if part not in baseUrlParts])

    queryString = urllib.parse.urljoin(opdsBaseURL, combinedPath).removesuffix('/')
    
    if queries:
        queryString = f'{queryString}?' + '&'.join(f'{key}={value}' for key,value in queries.items(multi=True))
    
    if request.path.startswith('/download'):
        downloadResponse = download_handler(combinedPath)
        return send_file(os.path.abspath(downloadResponse), as_attachment=True, download_name='test.mobi',
                        mimetype='application/x-mobipocket-ebook')

    
    # return queryString
    response = requests.get(queryString, auth=(user, password))
    if response.status_code == 200:
        feed = feedparser.parse(response.content)
        htmlOut = ""
        htmlOut = html_maker(response)
                
        # htmlOut = htmlOut + f"You wanted: {path} with querys: {queries}"

        # htmlOut = queries
        htmlOut = htmlOut + queryString + f"<br>{opdsBaseURL} <br><b>{urllib.parse.urljoin(opdsBaseURL, path)}</b>"
        return(htmlOut)
    else:
        return("Error")


if __name__ == '__main__':
    app.run(debug=True, host="0.0.0.0")



