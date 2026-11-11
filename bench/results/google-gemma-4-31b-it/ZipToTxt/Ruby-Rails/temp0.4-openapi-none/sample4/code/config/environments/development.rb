require "rails/env/development"

module ZipToTxt
  class Development < Rails::Application
    config.threshold_level = :debug

    # Stop logger from flooding the console in development
    config.logger = ActiveSupport::Logger.new(STDOUT)
    
    config.active_storage.service = :local
  end
end