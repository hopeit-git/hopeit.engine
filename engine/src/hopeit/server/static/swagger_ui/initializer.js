"use strict";

window.ui = SwaggerUIBundle({
  url: new URL("./swagger.json", window.location.href).href,
  dom_id: "#swagger-ui",
  deepLinking: true,
  validatorUrl: null,
  presets: [SwaggerUIBundle.presets.apis],
  layout: "BaseLayout",
});
