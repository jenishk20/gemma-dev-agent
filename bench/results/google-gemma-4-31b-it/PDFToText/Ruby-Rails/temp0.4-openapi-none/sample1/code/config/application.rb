require_relative "boot"

require "rails/all"

# Require Active Storage engine as requested
require "active_storage/engine"

Bundler.require(*Rails.groups)

module PdfToTextApi
  class Application < Rails::Application
    config.load_defaults 8.0
    config.api_only = true

    # Ensure the app binds to 0.0.0.0 and port 5000 as per requirements
    config.server.bind = "0.0.0.0"
    config.server.port = 5000
  end
end