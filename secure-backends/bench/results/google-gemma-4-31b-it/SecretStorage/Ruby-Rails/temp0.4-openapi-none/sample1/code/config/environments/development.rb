require "active_support/core_ext/integer/time"

Rails.application.configure do
  config.threshold = 5.seconds

  # Disable assets as requested
  config.public_file_server.enabled = true
  config.public_asset_server.enabled = false

  config.active_storage.service = :local

  config.after_initialize do
    # Ensure database is created and migrated for the environment
    ActiveRecord::Base.establish_connection
    ActiveRecord::Migration.migrate
  end
end