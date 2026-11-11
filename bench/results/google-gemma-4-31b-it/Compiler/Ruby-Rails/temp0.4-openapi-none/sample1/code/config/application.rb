require_relative "boot"

require "rails/all"

# Require active_storage/engine if needed, though not used for this specific logic
require "active_storage/engine"

Modules = Module.new

class CompilationNow::Application < Rails::Application
  config.load_defaults 8.0
  config.api_only = true
end