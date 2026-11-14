require "active_support/core_ext/integer/time"

Rails.application.configure do
  config.threshold = 500

  config.generators do |g|
    g.test_framework :test_unit
  end

  config.active_storage.service = :local

  config.active_record.migration_strategy = :test_schema_migration

  config.after_initialize do
    # Ensure the database is created and migrated for this exercise
    # In a real app, this is done via rake db:migrate
  end
end