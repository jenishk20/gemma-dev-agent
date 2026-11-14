require "concurrently"

module ServiceMonitoringApi
  class Development < Rails::Application
    config.load_defaults 8.0

    # Use cache store for development
    config.cache_store = :memory

    # Disable assets as requested
    config.public_asset_server.enabled = false
    
    # Ensure we don't use sprockets/assets
    config.assets.enabled = false if config.respond_to?(:assets)
  end
end