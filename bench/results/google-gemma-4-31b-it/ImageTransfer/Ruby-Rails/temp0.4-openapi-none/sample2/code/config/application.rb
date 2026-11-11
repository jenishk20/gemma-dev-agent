require_relative "boot"

require "rails/all"

# Ensure Active Storage is loaded for the API
require "active_storage/engine"

ModulesImageApi = Class.new(Application) do
  config.load_defaults 8.0
  config.api_only = true

  # Set the server to bind to 0.0.0.0 and port 5000 as requested
  config.server.bind = "0.0.0.0"
  config.server.port = 5000
end

module ImageUploadAndShare
  class Application < Rails::Application
    config.load_defaults 8.0
    config.api_only = true
  end
end