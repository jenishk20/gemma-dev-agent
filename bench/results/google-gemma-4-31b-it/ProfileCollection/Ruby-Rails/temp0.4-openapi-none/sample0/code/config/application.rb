require_relative "boot"

require "rails/all"

# Require Active Storage engine for file uploads
require "active_storage/engine"

Bundler.require(*Rails.groups)

module ProfileCollection
  class Application < Rails::Application
    config.load_defaults 8.0
    config.api_only = true

    # Ensure the app secret is set from environment variable
    config.secret_key_base = ENV["APP_SECRET"]
  end
end