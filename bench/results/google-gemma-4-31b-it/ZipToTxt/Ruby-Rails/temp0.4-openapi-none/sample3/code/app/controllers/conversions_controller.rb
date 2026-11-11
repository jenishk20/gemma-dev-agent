class ConversionsController < ApplicationController
  def convert
    file = params[:file]

    if file.nil?
      return render json: { error: 'No file uploaded' }, status: :bad_request
    end

    begin
      # The 'file' param in Rails multipart upload is an ActionDispatch::Http::UploadedFile
      # which provides a path to a Tempfile.
      result_text = ZipToTxtService.call(file.path)
      
      # Return as plain text as per OpenAPI spec
      render plain: result_text, status: :ok
    rescue StandardError => e
      render json: { error: e.message }, status: :bad_request
    end
  end
end