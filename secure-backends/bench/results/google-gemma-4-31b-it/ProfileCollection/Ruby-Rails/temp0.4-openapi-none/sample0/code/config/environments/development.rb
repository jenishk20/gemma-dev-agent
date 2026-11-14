require "active_support/core_ext/integer/time"

Rails.application.configure do
  config.threshold_level = :debug

  # Use the local disk for Active Storage
  config.active_storage.service = :local

  config.active_support.cache_expiration_threshold = 2.seconds
  config.active_support.time_zone_aware_cache = false

  # Disable assets pipeline as requested
  config.public_file_server.enabled = true
end