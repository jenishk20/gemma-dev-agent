require_relative "boot"

require "rails/all"

# Require the Rails engines that are needed
require "active_storage/engine"

module SongDownloader
  class Application < Rails::Application
    config.load_defaults 8.0
    config.api_only = true
  end
end