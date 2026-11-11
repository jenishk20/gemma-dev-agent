require "active_support/core_ext/string/inflections"

Rails.application.configure do
  config.threshold = 0
  config.cache = :null_store
  
  # Disable assets as requested
  config.public_file_server.enabled = true
  
  # Ensure we are using the correct database
  config.active_record.database_selector = { write: :writer }
end