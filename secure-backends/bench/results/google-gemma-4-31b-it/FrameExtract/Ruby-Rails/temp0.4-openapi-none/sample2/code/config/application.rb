require_relative "boot"

require "rails/all"

# Require Active Storage engine for file handling
require "active_storage/engine"

Bundler.require(*Rails.groups)

module FrameExtract
  class Application < Rails::Application
    config.load_defaults 8.0
    config.server.default_url_options = { host: '0.0.0.0', port: 5000 }
  end
end