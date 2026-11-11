require "active_support/core_ext/integer/time"

Rails.application.configure do
  # Set ActiveRecord to verbose mode when which logs queries.
  config.active_record.verbose_logging = true

  # Configure default storage for active storage
  config.active_storage.service = :local

  # Set the database to use sqlite3 as requested
  config.active_record.database_selector = { delay: 5 }
  
  # Ensure we don't use asset pipeline as requested
  config.public_file_server.enabled = true
end