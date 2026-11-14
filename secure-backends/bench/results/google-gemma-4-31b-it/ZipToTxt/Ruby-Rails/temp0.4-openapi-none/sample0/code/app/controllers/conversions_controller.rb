require 'zip'

class ConversionsController < ApplicationController
  def convert
    file = params[:file]

    if file.nil? || !file.respond_to?(:path)
      return render json: { error: "Invalid input: Please provide a zip file" }, status: :bad_request
    end

    begin
      result_text = ZipToTxtService.new(file.path).call
      render plain: result_text, content_type: 'text/plain'
    rescue => e
      render json: { error: "Conversion failed: #{e.message}" }, status: :bad_request
    end
  end
end