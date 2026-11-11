require_relative "boot"

require "rails/all"

# Require Active Storage engine as requested
require "active_storage/engine"

Modules = Module.new

class Application < Rails::Application
  config.load_defaults 8.0.1
  config.api_only = true
end