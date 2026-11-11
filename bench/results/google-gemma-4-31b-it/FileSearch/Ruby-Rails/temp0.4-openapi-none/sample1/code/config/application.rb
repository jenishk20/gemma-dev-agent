require_relative "boot"

require "rails/all"

# Require Active Storage engine as requested
require "active_storage/engine"

Bundler.require(*Rails.groups)

module FileSearch
  class Application < Rails::Application
    config.load_defaults 8.0
    config.api_only = true
  end
end