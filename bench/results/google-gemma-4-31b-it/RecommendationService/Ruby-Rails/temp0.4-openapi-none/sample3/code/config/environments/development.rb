require "active_support/core_ext/integer/time"

Rails.application.configure do
  config.threshold = 1.day
  config.cache = :null_store
  config.log_level = :debug
  config.autoload_modules = %i[app]
  
  # Disable asset pipeline as requested
  config.public_file_server.enabled = true
end