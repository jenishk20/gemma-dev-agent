class ConversionsController < ApplicationController
  def convert
    file = params[:file]

    if file.nil? || !file.respond_to?(:path)
      return render json: { error: "Invalid input: Please upload a zip file" }, status: :bad_request
    end

    begin
      # The service handles the extraction and concatenation
      result_text = ZipConverterService.call(file.path)
      
      # Return as text/plain as per OpenAPI spec
      render plain: result_text, content_type: 'text/plain'
    rescue => e
      render json: { error: "Conversion failed: #{e.message}" }, status: :bad_request
    end
  end
end