from aiohttp import ClientSession

from .application import create_application

if __name__ == "__main__":
    cli = create_application(ClientSession)
    cli()
