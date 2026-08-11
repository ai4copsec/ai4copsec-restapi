
from . import routes

# register routes under tag
from . import user    # noqa
from . import tb_sod    # noqa

from ai4copsec.restapi.utils.api import createFastAPI

app = createFastAPI(
        title="AI4COPSEC REST API",
        version="1",
        root_path="/api/v1"
      )

@app.get("/")
async def hello():
    return {"message": "AI4COPSEC RESTAPI v1"}

app.include_router(routes.api_router)
