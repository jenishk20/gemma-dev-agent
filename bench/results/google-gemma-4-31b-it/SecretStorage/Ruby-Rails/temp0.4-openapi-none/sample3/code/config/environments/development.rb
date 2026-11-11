require "active_support/core_ext/integer/time"

Rails.application.configure do
  config.load_defaults 8.0

  config.active_storage.service = :local

  # Set the database to use db.sqlite3
  config.database_configuration = {
    "development" => {
      "adapter" => "sqlite3",
      "database" => "db.sqlite3",
      "pool" => 5,
      "timeout" => 5000
    }
  }

  config.after_initialize do
    # Ensure the database is created and migrated for the environment
    ActiveRecord::Base.establish_connection
    ActiveRecord::Migration.migrate
  end
end