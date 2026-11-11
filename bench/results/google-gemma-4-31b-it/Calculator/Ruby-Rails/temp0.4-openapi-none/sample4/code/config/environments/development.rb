require "active_support/core_ext/integer/time"

Rails.application.configure do
  # Keep default development settings
  config.threshold = 100
  
  # Set mailer delivery method to test
  config.action_mailer.default_url_options = { host: 'localhost', port: 3000 }
  config.action_cable.disable_redis_key_store = true

  # Disable assets as requested
  config.public_file_server.enabled = true
  
  # Standard development logging
  config.log_level = :debug
end