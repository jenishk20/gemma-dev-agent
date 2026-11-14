require_relative "boot"

require "rails/all"

# Require Active Storage engine as requested
require "active_storage/engine"

Bundler.require(*Rails.groups)

module FrameExtract
  class Application < Rails::Application
    config.load_defaults 8.0
    config.api_only = true

    # Ensure we can handle the file uploads and responses
    config.middleware.insert_before 0, Rack::Cors do
      allow do
        origins '*'
        resource '*', headers: :any, methods: [:get, :post, :options]
      end
    end
  end
end