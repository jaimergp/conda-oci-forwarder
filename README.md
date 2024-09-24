# conda-oci-forwarder

Serve OCI/ORAS artifacts from [ghcr.io/channel-mirrors](https://github.com/orgs/channel-mirrors/packages) so conda clients see them as if they were coming from a regular HTTP channel.

## Try the online demo

There's an online deployment available for public testing. Do NOT use in production because it is very unlikely this small server would be able to cope with real-world demands:

```bash
$ conda create --name oci-fwd-tests --override-channels -c https://condaociforwarder-6p3byq6z.b4a.run/conda-forge python
```

## Run locally

If you really need this for production use, your best chance right now is to run the server locally.

1. Clone this repository and `cd` there.
2. Build the Docker container: `docker build .`.
3. Write down the hash of the last build (first row, ID field): `docker images`.
4. Run the Docker container: `docker run -p 8000:8000 <hash output from step 3>`.
5. Try it out at http://0.0.0.0:8000:

```bash
$ conda create --name oci-fwd-tests --override-channels -c http://0.0.0.0:8000/conda-forge python
```

## Disclaimer

This is a very early prototype meant for testing, playing around and getting out of emergency situations. It's possible that there are rough edges. Report in the Issues tab if necessary!
