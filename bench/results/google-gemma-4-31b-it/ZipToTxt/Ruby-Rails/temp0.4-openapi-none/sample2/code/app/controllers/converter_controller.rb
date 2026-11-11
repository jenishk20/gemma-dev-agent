class ConverterController < ApplicationController
  def convert
    file = params[:file]

    if file.nil? || !file.respond_to?(:tempfile)
      return render json: { error: "Invalid input: Please provide a zip file" }, status: :bad_request
    end

    begin
      result_text = ZipToTxtService.call(file.path)
      render plain: result_text, content_type: 'text/plain'
    rescue StandardError => e
      render json: { error: "Conversion failed: #{e.message}" }, status: :bad_request
    end
  end
end