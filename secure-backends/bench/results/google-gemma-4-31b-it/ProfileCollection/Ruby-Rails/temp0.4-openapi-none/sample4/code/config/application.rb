require_relative "boot"

require "rails/all"

# Require Active Storage engine for file uploads
require "active_storage/engine"

module ProfileCollection
  class Application < Rails::Application
    config.load_defaults 8.0
    config.secret_key_base = ENV["APP_SECRET"] || "default_secret_for_dev"
  end
end