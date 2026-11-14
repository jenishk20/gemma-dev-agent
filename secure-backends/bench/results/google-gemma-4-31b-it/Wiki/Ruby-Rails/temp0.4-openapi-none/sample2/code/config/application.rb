require_relative "boot"

require "rails/all"

# Require the rails components
require "active_storage/engine"

Modules = Module.new

class WikiApp < Rails::Application
  config.load_defaults 8.0
  config.api_only = true
end