# hopeit.engine maintenance scripts

Keep instructions, code comments, and documentation in English. Follow
hopeit.engine's existing conventions and keep maintenance scripts small.

## Updating RapiDoc

RapiDoc is bundled locally for the engine's OpenAPI documentation. The updater
uses Python's standard library; no Node.js, npm installation, frontend build, or
additional runtime dependency is needed.

Run commands from the repository root, using the existing development environment.

1. Select an official `rapidoc` release from
   [npm](https://www.npmjs.com/package/rapidoc). Read its metadata at
   `https://registry.npmjs.org/rapidoc/<version>` and obtain `version` and
   `dist.integrity` for that exact release.
2. Update `VERSION` and `INTEGRITY` in `engine/scripts/rapidoc/update_rapidoc.py`.
   Keep the SHA-512 integrity check. Do not derive the expected checksum from
   the downloaded archive or edit the generated bundle manually.
3. Download and install the pinned assets:

   ```sh
   uv run --no-sync python engine/scripts/rapidoc/update_rapidoc.py
   ```

   The script verifies the archive before writing `rapidoc-min.js`, `LICENSE.txt`,
   and `VERSION` into `engine/src/hopeit/server/static/rapidoc/`.
4. Update the RapiDoc version in `THIRDPARTY` and the bundle version assertion in
   `engine/test/integration/server/test_it_openapi.py`. Retain the release's license.
5. Run the OpenAPI integration tests:

   ```sh
   PYTHONPATH=engine/src:engine/test uv run --no-sync pytest -q engine/test/integration/server/test_it_openapi.py
   ```

6. Check the documentation in a browser using an example app. Verify spec loading,
   authentication declared by the generated spec, tracking headers, JSON requests,
   and multipart requests with data fields and streamed file attachments. Confirm
   that the UI assets and fonts do not require external requests.

Keep the existing `docs_path`, `swagger.json` URL, and relative asset URLs. Preserve
`load-fonts="false"` and the simple HTML integration in
`engine/src/hopeit/server/openapi.py` and
`apps/examples/simple-example/api/index_templates.html`. A UI update must not change
request validation, authentication enforcement, or multipart streaming behavior.

If the release changes its asset layout, adjust `FILES` and the package-data entry
in `engine/pyproject.toml` as needed. Build the distribution and verify that the wheel
and source archive contain all required local assets and license files:

```sh
uv build --project engine --out-dir /tmp/hopeit-rapidoc-dist
```

Commit the updater, generated assets, version references, and relevant tests
together. Add a release note only when the update changes user-visible behavior.
