class ConverterController < ApplicationController
  def convert
    file = params[:file]

    if file.nil? || !file.respond_to?(:path)
      return render json: { error: "Missing file or invalid upload" }, status: :bad_request
    end

    unless file.content_type == 'application/pdf'
      return render json: { error: "Uploaded file must be a PDF" }, status: :bad_request
    end

    begin
      # pdftotext [input-file] - outputs to stdout if no output file is specified
      # We use the '-' as the second argument to tell pdftotext to send output to stdout
      text_content = `pdftotext "#{file.path}" -`
      
      render plain: text_content, status: :ok
    rescue StandardError => e
      render json: { error: "Conversion failed: #{e.message}" }, status: :internal_server_error
    end
  end
end