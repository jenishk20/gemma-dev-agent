require "active_support/core_ext/integer/time"

Rails.application.configure do
  # Use the provided secret
  config.secret_key_base = ENV["APP_SECRET"] || "a_very_long_random_string_for_development"

  # Standard development settings
  config.cache_store = :memory_cache
  config.log_level = :debug

  # Ensure we don't use assets pipeline as requested
  config.public_file_server.enabled = true
end