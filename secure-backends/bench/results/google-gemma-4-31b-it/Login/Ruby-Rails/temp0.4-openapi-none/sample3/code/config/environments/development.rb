require "active_support/core_ext/integer/time"

Rails.application.configure do
  config.rails_env = "development"
  config.cache_store = :memory_store
  config.log_level = :debug

  # Disable assets as requested
  config.public_file_server.enabled = true
end