class LogsController < ApplicationController
  LOG_FILE = Rails.root.join('logs.txt')

  # POST /log
  def create
    message = params[:message]
    
    if message.present?
      # Append the message to the file with a newline
      File.open(LOG_FILE, 'a') do |f|
        f.puts(message)
      end
      head :ok
    else
      render json: { error: "Message is required" }, status: :bad_request
    end
  end

  # GET /logs
  def index
    if File.exist?(LOG_FILE)
      # Read the entire file content
      content = File.read(LOG_FILE)
      render plain: content
    else
      # Return empty string if file doesn't exist yet
      render plain: ""
    end
  end
end