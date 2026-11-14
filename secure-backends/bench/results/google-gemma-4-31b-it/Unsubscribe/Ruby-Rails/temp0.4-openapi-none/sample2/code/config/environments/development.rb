require "active_support/core_ext/interior"

# Configure this file for the development environment.
Rails.application.configure do
  # Keep all logger output visible in the console
  config.logger = ActiveSupport::Logger.new(STDOUT)

  # Set the level of the logger
  config.log_level = :debug

  # Raise exceptions in development
  config.consider_all_requests_local = true

  # Use the default caching strategy
  config.cache_store = :memory_cache
end