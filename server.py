import os
import asyncio
import logging
import argparse
from functools import partial

import aiofiles
from aiohttp import web
from environs import Env

logger = logging.getLogger(__name__)


async def archive(request: web.Request, path_to_folder: str,
                  delay: bool) -> web.StreamResponse:
    response = web.StreamResponse()
    name = request.match_info.get('archive_hash', 'archive')
    logger.info(f'Trying to download catalog "{name}"\n')

    response.enable_chunked_encoding()

    response.headers['Content-Disposition'] = \
        f'attachment; filename="{name}.zip"'

    path = os.path.join(path_to_folder, name)
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

    try:
        while True:
            if proc.stdout.at_eof():
                await asyncio.sleep(0.05)   # с этой задержкой процесс убивается до блока finally
                break
            chunk = await proc.stdout.read(n=50000)
            logger.info('Sending archive chunk ...')
            await response.write(chunk)
            if delay:
                await asyncio.sleep(0.05)
    finally:
        if proc.returncode is not None:
            logger.info('Download completed\n')
        else:
            proc.kill()
            await proc.communicate()
            logger.info('Download failed\n')

    return response


async def handle_index_page(request: web.Request) -> web.Response:
    async with aiofiles.open('index.html', mode='r') as index_file:
        index_contents = await index_file.read()
    return web.Response(text=index_contents, content_type='text/html')


def main():
    env = Env()
    env.read_env()
    path_to_folder = env.str('PATH_TO_FOLDER')
    parser = argparse.ArgumentParser(
        description='Программа позволяет скачивать папки с фото архивом',
    )
    parser.add_argument('--log', '-l', action=argparse.BooleanOptionalAction,
                        help='Аргумент активирует логи')
    parser.add_argument('--delay', '-d', action=argparse.BooleanOptionalAction,
                        help='Включение задержки при скачивании')
    args = parser.parse_args()
    logging.basicConfig(
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        level=logging.INFO
    )
    logger.setLevel(logging.INFO)
    logger.disabled = True if not args.log else False

    app = web.Application()
    app.add_routes([
        web.get('/', handle_index_page),
        web.get('/archive/{archive_hash}/',
                partial(
                    archive,
                    path_to_folder=path_to_folder,
                    delay=args.delay
                        )
                ),
    ])
    logger.info('Starting microservice')
    web.run_app(app)


if __name__ == '__main__':
    main()
