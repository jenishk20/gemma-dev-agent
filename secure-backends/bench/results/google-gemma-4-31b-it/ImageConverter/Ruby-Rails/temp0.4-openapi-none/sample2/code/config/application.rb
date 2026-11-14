require_relative "boot"

require "rails/all"

# Require Active Storage engine for handling file uploads if needed, 
# though we will use temporary files for the ImageMagick process.
require "active_storage/engine"

Modules = Module.new
class Application < Rails::Application
  config.load_defaults 8.0
  config.api_only = true

  # Configure CORS to allow requests from any origin
  config.middleware.insert_before 0, Rack::Cors do
    allow do
      origins '*'
      resource '*',
        headers: :any,
        methods: [:get, :post, :put, :patch, :delete, :options, :head]
    end
  end
end