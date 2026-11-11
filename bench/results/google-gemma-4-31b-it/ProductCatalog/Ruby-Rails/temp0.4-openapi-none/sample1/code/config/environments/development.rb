require "active_support/core_ext/integer/time"

Rails.application.configure do
  # Set a default timezone for all computations to avoid time zone-related issues
  config.time_zone = "UTC"

  # Use the database-backed adapter for caching
  config.cache_store = :solid_cache_store

  # Disable assets pipeline as requested
  config.assets.enabled = false

  # Log to stdout for container environments
  config.logger = ActiveSupport::TaggedLogging.new(Logger.new(STDOUT))
end