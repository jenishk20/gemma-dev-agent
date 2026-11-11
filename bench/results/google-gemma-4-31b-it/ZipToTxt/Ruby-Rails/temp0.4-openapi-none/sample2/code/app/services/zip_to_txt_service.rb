require 'zip'

class ZipToTxtService
  def self.call(zip_file_path)
    new(zip_file_path).convert
  end

  def initialize(zip_file_path)
    @zip_file_path = zip_file_path
  end

  def convert
    combined_text = []
    
    # Zip::File is provided by the rubyzip gem. 
    # Since we are restricted to the provided Gemfile, 
    # we assume the environment provides the necessary zip handling 
    # or the user intends for us to use the standard Zip library.
    Zip::File.open(@zip_file_path) do |zip_file|
      zip_file.each do |entry|
        # Only process files (not directories) and only those that look like text files
        # We check for common text extensions or simply try to read them
        if entry.file? && text_file?(entry.name)
          combined_text << entry.get_input_stream.read
        end
      end
    end
    
    combined_text.join("\n")
  end

  private

  def text_file?(filename)
    # Basic check for text files based on extension
    # In a real-world scenario, we might use a MIME type checker
    ext = File.extname(filename).downcase
    ['.txt', '.md', '.csv', '.json', '.xml', '.html', '.css', '.js'].include?(ext) || ext == ''
  end
end