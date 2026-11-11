require_relative "boot"

require "rails/all"

# Require activesupport hosted engine
require "active_storage/engine"

module WikiApp
  class Application < Rails::Application
    config.load_defaults 8.0
    config.api_only = true # We keep API mode but can still render HTML/JSON
  end
end