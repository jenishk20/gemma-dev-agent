require_relative "boot"

require "rails/all"

# Require Active Storage engine for file handling if needed, 
# though we will use Tempfile for this specific utility.
require "active_storage/engine"

Modules = Module.new
class Application < Rails::Application
  config.load_defaults 8.0
  config.api_only = true

  # Ensure the app is configured for the API mode
  config.middleware.use Rack::Cors do
    allow do
      origins '*'
      resource '*', headers: :any, methods: [:get, :post, :put, :patch, :delete, :options, :head]
    end
  end
end