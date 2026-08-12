from ai4copsec.restapi.utils.api import createFastAPI

# register routes under tag
from . import (
    routes,
    tb_algorithms,  # noqa
    tb_dan,  # noqa
    tb_shi,  # noqa
    tb_sod,  # noqa
    tb_trp,  # noqa
    user,  # noqa
)

app = createFastAPI(title="AI4COPSEC REST API", version="1", root_path="/api/v1")


@app.get("/")
async def hello():
    return {"message": "AI4COPSEC RESTAPI v1"}


app.include_router(routes.api_router)
