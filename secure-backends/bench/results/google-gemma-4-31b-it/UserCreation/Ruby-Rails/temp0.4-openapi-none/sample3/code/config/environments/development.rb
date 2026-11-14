require "active_support/all"

InviteApi::Application.configure do
  config.load_defaults 8.0

  # Use SQLite for development
  config.database_configuration = {
    "development" => {
      "adapter" => "sqlite3",
      "database" => "db.sqlite3",
      "pool" => 5,
      "timeout" => 5000
    }
  }

  config.active_storage.service = :local

  # Set logger to debug
  config.log_level = :debug
end