require_relative "boot"

require "rails/all"

# Require Active Storage engine for file handling
require "active_storage/engine"

Modules = Module.new

class Application < Rails::Application
  config.load_defaults 8.0
  config.api_only = true
  
  # Ensure we can handle multipart form data
  config.middleware.insert_before Rack::Runtime, Rack::Cors do
    allow do
      origins '*'
      resource '*', headers: :any, methods: [:get, :post, :options, :put, :patch, :delete]
    end
  end
end