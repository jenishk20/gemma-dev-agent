require_relative "boot"

require "rails/all"

# Require the rails components
require "active_storage/engine"

ModulesWikiApi = Class.new(Rails::Application) do
  config.load_defaults 8.0
  config.server.binding = "0.0.0.0"
  config.server.port = 5000
end