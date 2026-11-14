require "active_support/core_ext/integer/time"

Rails.application.configure do
  # Set default adapter for all caching
  config.cache_store = :memory_cache
  
  # Log to stdout for container environments
  config.logger = ActiveSupport::Logger.new(STDOUT)
  
  # Ensure the app doesn't try to load assets
  config.public_file_server.enabled = true
  
  # Standard development settings
  config.consider_all_requests_local = true
  config.force_ssl = false
end