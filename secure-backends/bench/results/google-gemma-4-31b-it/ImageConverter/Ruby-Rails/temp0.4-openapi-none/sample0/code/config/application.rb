require_relative "boot"

require "rails/all"

# Require Active Storage engine for file handling
require "active_storage/engine"

Modules = Module.new

class Application < Rails::Application
  config.load_defaults 8.0.1
  config.server. Puma = Puma
end