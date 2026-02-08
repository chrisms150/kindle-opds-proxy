from flask import Flask, request, send_file, Response, after_this_request, send_from_directory
import requests
import feedparser
import urllib
import subprocess
import os
import time
import re
import shutil

app = Flask(__name__)

# Cache folder configuration
CACHE_FOLDER = "cache"

# Ensure cache folder exists
os.makedirs(CACHE_FOLDER, exist_ok=True)

opds_url = os.getenv('OPDS_URL')
opds_urlParsed = urllib.parse.urlsplit(opds_url)
opdsBaseURL = urllib.parse.urlunsplit(
    (opds_urlParsed.scheme, opds_urlParsed.netloc, opds_urlParsed.path, '', ''))
opdsBaseURL = opdsBaseURL+'/'
baseUrlParts = [x for x in opds_urlParsed.path.split('/') if x]
user = os.getenv('OPDS_USER')
password = os.getenv('OPDS_PASSWORD')


def normalize_opds_path(href: str) -> str:
    parsed = urllib.parse.urlsplit(href)
    if parsed.scheme and parsed.netloc:
        path = parsed.path
        query = f'?{parsed.query}' if parsed.query else ''
    else:
        path = href
        query = ''

    return '/' + path.lstrip('/') + query


def safe_filename(name: str, fallback: str = "book") -> str:
    if not name:
        return fallback
    cleaned = re.sub(r'[^A-Za-z0-9 _.-]', '', name).strip()
    cleaned = re.sub(r'\s+', '_', cleaned)
    return cleaned or fallback


def html_maker(response, show_back=False):
    feed = feedparser.parse(response.content)
    htmlOut = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=0.8">
        <link rel="stylesheet" href="/static/style.css">
    </head>
    <body>
    """
    if show_back:
        htmlOut += '<p class="back-link"><a href="/">&larr; Back</a></p>'
    htmlOut += f'<h1>{feed.feed.title}</h1>'
    htmlOut += '<hr>'
    htmlOut += '<ul class="book-list">'

    for entry in feed.entries:
        if 'links' not in entry:
            continue

        nav_href = None
        download_href = None
        cover_href = None
        authors = ', '.join([a.get('name', '') for a in entry.get(
            'authors', [])]) if entry.get('authors') else ''
        summary = entry.get('summary', '') or ''

        for link in entry.links:
            rel = str(link.rel)
            href = link.href

            if rel in ('subsection', 'alternate') and not nav_href:
                nav_href = normalize_opds_path(href)
                continue

            if rel == 'http://opds-spec.org/acquisition' and not download_href:
                rel_path = normalize_opds_path(href)
                if not rel_path.startswith('/'):
                    rel_path = '/' + rel_path
                filename = safe_filename(entry.title, "book")
                sep = '&' if '?' in rel_path else '?'
                download_href = f"/download{rel_path}{sep}filename={urllib.parse.quote(filename)}"

            if rel in ('http://opds-spec.org/image/thumbnail', 'http://opds-spec.org/image') and not cover_href:
                cover_href = f"/cover?href={urllib.parse.quote(href, safe='')}"

        if download_href:
            q_title = urllib.parse.quote(entry.title or '', safe='')
            q_authors = urllib.parse.quote(authors, safe='')
            q_summary = urllib.parse.quote(summary, safe='')
            q_cover = urllib.parse.quote(cover_href or '', safe='')
            download_base = download_href.split(
                '?')[0] if '?' in download_href else download_href
            q_download = urllib.parse.quote(download_base, safe='/')
            target_href = f"/book?title={q_title}&authors={q_authors}&summary={q_summary}&cover={q_cover}&download={q_download}"
        else:
            target_href = nav_href

        if not target_href:
            continue

        htmlOut += f'<li class="book-item"><a href="{target_href}"><span class="book-title">{entry.title}</span></a></li>'

    htmlOut += """
    </ul>
    </body>
    </html>
    """
    return htmlOut


def convert_epub_to_mobi_calibre(epub_file_path, mobi_output_path, download_name='book.mobi'):
    command = ['ebook-convert', epub_file_path, mobi_output_path]

    try:
        subprocess.run(command, check=True,
                       stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        return send_file(
            os.path.abspath(mobi_output_path),
            as_attachment=True,
            download_name=download_name
        )
    except subprocess.CalledProcessError as e:
        return (f"Error during conversion: {e.stderr.decode()}")
    except FileNotFoundError:
        return ("Error: ebook-convert not found. Make sure Calibre is installed and in your PATH.")


def download_handler(path):
    cleaned = path.lstrip('/')
    path_without_download = cleaned.removeprefix('download/')
    opds_origin = f"{opds_urlParsed.scheme}://{opds_urlParsed.netloc}"
    downloadURL = urllib.parse.urljoin(
        opds_origin + '/', path_without_download)

    qs = request.query_string.decode()
    if qs:
        downloadURL = f"{downloadURL}{'&' if '?' in downloadURL else '?'}{qs}"

    print(f"DEBUG: Trying to download from: {downloadURL}")
    print(f"DEBUG: Original path: {path}")

    response = requests.get(downloadURL, stream=True, auth=(user, password))
    if response.status_code != 200:
        return (f"Failed to download. Status: {response.status_code}")

    filename_hint = safe_filename(request.args.get('filename', ''), 'book')
    if filename_hint == 'book':
        base_candidate = os.path.basename(
            urllib.parse.urlsplit(path_without_download).path)
        base_candidate = base_candidate.rsplit('.', 1)[0]
        filename_hint = safe_filename(base_candidate, 'book')

    timestamp = str(int(time.time()))
    epub_path = os.path.join(CACHE_FOLDER, f"book_{timestamp}.epub")
    mobi_path = os.path.join(CACHE_FOLDER, f"book_{timestamp}.mobi")

    with open(epub_path, "wb") as f:
        for chunk in response.iter_content(chunk_size=8192):
            f.write(chunk)

    @after_this_request
    def cleanup(response):
        def delayed_cleanup():
            time.sleep(10)
            try:
                if os.path.exists(CACHE_FOLDER):
                    for filename in os.listdir(CACHE_FOLDER):
                        file_path = os.path.join(CACHE_FOLDER, filename)
                        try:
                            if os.path.isfile(file_path) or os.path.islink(file_path):
                                os.unlink(file_path)
                            elif os.path.isdir(file_path):
                                shutil.rmtree(file_path)
                        except Exception as e:
                            print(f"Failed to delete {file_path}: {e}")
                    print(f"Cleaned up cache folder: {CACHE_FOLDER}")
            except Exception as e:
                print(f"Cleanup error: {e}")

        import threading
        threading.Thread(target=delayed_cleanup, daemon=True).start()
        return response

    convertResponse = convert_epub_to_mobi_calibre(
        epub_path, mobi_path, download_name=f"{filename_hint}.mobi")
    return convertResponse


@app.route('/static/<path:filename>')
def serve_static(filename):
    return send_from_directory('static', filename)


@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def landing_page(path):
    search_query = request.args.get('query', default="")
    queries = request.args
    pathParts = [x for x in path.split('/') if x]
    combinedPath = '/'.join([part for part in pathParts if part not in baseUrlParts])

    if request.path.startswith('/download'):
        downloadResponse = download_handler(path)
        return downloadResponse

    queryString = urllib.parse.urljoin(
        opdsBaseURL, combinedPath).removesuffix('/')

    if queries:
        queryString = f'{queryString}?' + \
            '&'.join(f'{key}={value}' for key,
                     value in queries.items(multi=True))

    response = requests.get(queryString, auth=(user, password))
    if response.status_code == 200:
        show_back = request.path != '/'
        htmlOut = html_maker(response, show_back=show_back)
        return (htmlOut)
    else:
        return ("Error")


@app.route('/cover')
def cover_proxy():
    href = request.args.get('href', '')
    if not href:
        return Response("Missing href", status=400)

    target_url = href
    if not urllib.parse.urlsplit(href).scheme:
        target_url = urllib.parse.urljoin(opdsBaseURL, href)

    resp = requests.get(target_url, auth=(user, password), stream=True)
    if resp.status_code != 200:
        return Response(f"Failed to fetch cover (status {resp.status_code})", status=resp.status_code)

    content_type = resp.headers.get('Content-Type', 'image/jpeg')
    return Response(resp.content, status=200, content_type=content_type)


@app.route('/book')
def book_detail():
    title = request.args.get('title', '')
    authors = request.args.get('authors', '')
    summary = request.args.get('summary', '')
    cover = request.args.get('cover', '')
    download_base = urllib.parse.unquote(request.args.get('download', ''))

    if not download_base:
        return Response("Missing download link", status=400)

    filename = safe_filename(title, 'book')
    sep = '&' if '?' in download_base else '?'
    download = f"{download_base}{sep}filename={urllib.parse.quote(filename)}"

    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset=\"UTF-8\">
        <meta name=\"viewport\" content=\"width=device-width, initial-scale=0.8\">
        <link rel=\"stylesheet\" href=\"/static/style.css\">
    </head>
    <body>
        <p class=\"back-link\"><a href=\"/\">&larr; Back</a></p>
        <h1>{title} <a class=\"download-link\" href=\"{download}\">Download</a></h1>
        <hr>
        <div class=\"book-details\">
            {f'<img class="book-cover" src="{cover}" alt="Cover for {title}">' if cover else ''}
            <div class=\"book-info\">
                {f'<p class="book-author"><strong>By:</strong> {authors}</p>' if authors else ''}
                {f'<div class="book-summary">{summary}</div>' if summary else ''}
            </div>
        </div>
    </body>
    </html>
    """

    return Response(html, status=200, content_type='text/html')


if __name__ == '__main__':
    app.run(host='0.0.0.0')
