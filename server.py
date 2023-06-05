import os
import asyncio
import logging

import aiofiles
from aiohttp import web

logger = logging.getLogger(__name__)


async def archive(request):
    response = web.StreamResponse()
    name = request.match_info.get('archive_hash', 'archive')
    logger.info(f'Trying to download catalog "{name}"')

    response.headers['Content-Disposition'] = \
        f'attachment; filename="{name}.zip"'

    path = os.path.join('test_photos', name)
    try:
        proc = await asyncio.create_subprocess_exec(
            'zip', '-r', '-', '.', stdout=asyncio.subprocess.PIPE, cwd=path
        )
    except FileNotFoundError:
        logger.warning(f'Archive "{name}" does not exist or has been deleted')
        return web.HTTPNotFound(
            text=f'Архив "{name}" не существует или был удален.'
        )

    await response.prepare(request)

    while True:
        if proc.stdout.at_eof():
            break
        chunk = await proc.stdout.read(n=50000)
        logger.info('Sending archive chunk ...')
        await response.write(chunk)

    return response


async def handle_index_page(request):
    async with aiofiles.open('index.html', mode='r') as index_file:
        index_contents = await index_file.read()
    return web.Response(text=index_contents, content_type='text/html')


def main():
    logging.basicConfig(
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        level=logging.INFO
    )
    logger.setLevel(logging.INFO)
    app = web.Application()
    app.add_routes([
        web.get('/', handle_index_page),
        web.get('/archive/{archive_hash}/', archive),
    ])
    logger.info('Starting microservice')
    web.run_app(app)


if __name__ == '__main__':
    main()
