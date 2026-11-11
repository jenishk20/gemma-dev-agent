require 'zip'

class ZipToTxtService
  def initialize(zip_path)
    @zip_path = zip_path
  end

  def call
    combined_content = []

    Zip::File.open(@zip_path) do |zip_file|
      zip_file.each do |entry|
        # Only process files (not directories) and only those that look like text files
        # We check for common text extensions or simply attempt to read if it's not a directory
        if entry.file? && text_file?(entry.name)
          combined_content << entry.get_input_stream.read
        end
      end
    end

    combined_content.join("\n")
  end

  private

  def text_file?(filename)
    # Basic check for text files: common extensions or no extension (often text)
    # In a production app, we might use MIME type checking.
    extensions = ['.txt', '.md', '.csv', '.json', '.xml', '.html', '.css', '.js']
    ext = File.extname(filename).downcase
    extensions.include?(ext) || ext == ''
  end
end