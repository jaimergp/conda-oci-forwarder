"""
Serve OCI/ORAS artifacts from GHCR so conda sees it as a regular HTTP channel.

Run with 'fastapi run' and use from conda like 
'conda create --name oci-fwd-test --override-channels -c http://0.0.0.0:8000/conda-forge python'
"""

from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI
from fastapi.responses import RedirectResponse


OCI_ORG = "channel-mirrors"
OCI_REGISTRY = f"https://ghcr.io/v2/{OCI_ORG}"


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.httpx = httpx.AsyncClient()
    yield
    await app.httpx.aclose()


app = FastAPI(title="conda-oci-mirror-forwarder", lifespan=lifespan)
_PULL_TOKEN = None
_PULL_TOKEN_USES = 0  # simple cache to reuse tokens


async def fetch_pull_token(channel, subdir, package_name):
    global _PULL_TOKEN
    global _PULL_TOKEN_USES
    if _PULL_TOKEN is None or _PULL_TOKEN_USES > 100:
        r = await app.httpx.get(
            "https://ghcr.io/token?scope=repository:"
            f"{OCI_ORG}/{channel}%2F{subdir}%2F{package_name}:pull"
        )
        r.raise_for_status()
        token =  r.json()["token"]
        _PULL_TOKEN = token
        _PULL_TOKEN_USES = 0
    _PULL_TOKEN_USES += 1
    return _PULL_TOKEN


async def fetch_manifest(channel, subdir, package_name, version_build_tag, token):
    r = await app.httpx.get(
        f"{OCI_REGISTRY}/{channel}/{subdir}/{package_name}/manifests/{version_build_tag}",
        headers={
            "Accept": "application/vnd.oci.image.manifest.v1+json",
            "Authorization": f"Bearer {token}",
        },
    )
    r.raise_for_status()
    return r.json()


async def get_download_response(
    manifest, channel, subdir, package_name, extension, token
):
    if package_name == "repodata.json":
        if extension in (".zst", "zst"):
            media_type = "application/vnd.conda.repodata.v1+json+zst"
        else:
            media_type = "application/vnd.conda.repodata.v1+json"
    elif extension == ".tar.bz2":
        media_type = "application/vnd.conda.package.v1"
    else:
        media_type = "application/vnd.conda.package.v2"
    for layer in manifest["layers"]:
        if layer["mediaType"] == media_type:
            digest = layer["digest"]
            break
    else:
        raise ValueError(f"Couldn't find layer for {extension}")

    r = await app.httpx.get(
        f"{OCI_REGISTRY}/{channel}%2F{subdir}%2F{package_name}/blobs/{digest}",
        headers={
            "Accept": media_type,
            "Authorization": f"Bearer {token}",
        },
    )
    if not r.has_redirect_location:
        raise ValueError(f"Couldn't get redirect URL for {package_name}")
    return r


def parse_artifact(artifact: str):
    if artifact.startswith("repodata.json"):
        package_name = "repodata.json"
        tag = "latest"
        version = None
        build = None
        extension = artifact.split(".")[-1]
    else:
        for extension in (".tar.bz2", ".conda"):
            if artifact.endswith(extension):
                artifact = artifact[: -len(extension)]
                break
        else:
            raise ValueError("Needs to be .tar.bz2 or .conda")
        package_name, version, build = artifact.rsplit("-", 2)
        tag = f"{version}-{build}"
    return {
        "artifact": artifact,
        "package_name": package_name,
        "version": version,
        "build": build,
        "extension": extension,
        "tag": tag,
    }


@app.get("/{channel}/{subdir}/{artifact}")
async def redirect_to_download(channel, subdir, artifact):
    parsed = parse_artifact(artifact)
    token = await fetch_pull_token(
        channel,
        subdir,
        parsed["package_name"],
    )
    manifest = await fetch_manifest(
        channel,
        subdir,
        parsed["package_name"],
        parsed["tag"],
        token,
    )
    response = await get_download_response(
        manifest,
        channel,
        subdir,
        parsed["package_name"],
        parsed["extension"],
        token,
    )

    return RedirectResponse(
        response.headers["location"],
        headers=dict(response.headers),
    )
