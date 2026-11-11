require_relative "../application"

Rails.application.configure do
  config.threshold = 500

  # Standard API development settings
  config.after_initialize do
    # Ensure we are using the correct database file
    ActiveRecord::Base.establish_connection(
      adapter: 'sqlite3',
      database: 'db.sqlite3'
    )
  end

  # Disable assets as requested
  config.public_file_server.enabled = true
  
  # Log to stdout
  config.logger = ActiveSupport::Logger.new(STDOUT)
end