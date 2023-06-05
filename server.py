import asyncio
import os

import aiofiles
from aiohttp import web


async def archive(request):
    response = web.StreamResponse()
    name = request.match_info.get('archive_hash', 'archive')

    response.headers['Content-Disposition'] = f'attachment; filename="{name}.zip"'

    path = os.path.join('test_photos', name)
    try:
        proc = await asyncio.create_subprocess_exec(
            'zip', '-r', '-', '.', stdout=asyncio.subprocess.PIPE, cwd=path
        )
    except FileNotFoundError:
        return web.HTTPNotFound(text='Архив не существует или был удален.')

    await response.prepare(request)

    while True:
        if proc.stdout.at_eof():
            break
        piece = await proc.stdout.read(n=500)
        await response.write(piece)

    return response


async def handle_index_page(request):
    async with aiofiles.open('index.html', mode='r') as index_file:
        index_contents = await index_file.read()
    return web.Response(text=index_contents, content_type='text/html')


if __name__ == '__main__':
    app = web.Application()
    app.add_routes([
        web.get('/', handle_index_page),
        web.get('/archive/{archive_hash}/', archive),
    ])
    web.run_app(app)
