require "rails/all"

Rails.application.configure do
  config.load_defaults 8.0

  # Use SQLite3
  config.active_record.database_type = :sqlite3

  # Since this is an API, we don't need views or assets
  config.public_file_server.enabled = true

  # Set logger
  config.logger = ActiveSupport::Logger.new(STDOUT)
end